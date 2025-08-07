import threading
import dukpy

from css.css_parser import CSSParser
from htmltree.htmlparser import HTMLParser
from task import Task
from utils import tree_to_list
RUNTIME_JS = open("js/runtime.js").read()
EVENT_DISPATCH_JS = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"
SETTIMEOUT_JS = "__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_JS = "__runXHROnload(dukpy.out, dukpy.handle)"

class JSContext:
    def __init__(self, tab):
        self.tab = tab
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll",self.querySelectorAll)
        self.interp.export_function("getAttribute",self.getAttribute)
        self.interp.export_function("innerHTML_set",self.innerHTML_set)
        self.interp.export_function("setTimeout",self.setTimeout)
        self.interp.export_function("requestAnimationFrame", self.requestAnimationFrame)
        self.interp.evaljs(RUNTIME_JS)
        self.node_to_handle = {}
        self.handle_to_node = {}
        self.discarded = False

    def run(self, script, code):
        try:
            # Measure JS eval
            self.tab.browser.measure.time('evaljs run')
            result = self.interp.evaljs(code)
            self.tab.browser.measure.stop('evaljs run')
            return result
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)

    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
        nodes = [node for node
             in tree_to_list(self.tab.nodes, [])
             if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]

    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle

    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        attr = elt.attributes.get(attr, None)
        return attr if attr else ""

    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
        self.tab.browser.measure.time('evaljs dispatch_event ' + type)
        do_default = self.interp.evaljs(EVENT_DISPATCH_JS, type=type, handle=handle)
        self.tab.browser.measure.stop('evaljs dispatch_event ' + type)
        return not do_default

    def innerHTML_set(self, handle, s):
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        self.tab.set_needs_render()

    def XMLHttpRequest_send(
        self, method, url, body, isasync, handle):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != self.tab.url.origin():
            raise Exception(
                "Cross-origin XHR request not allowed")
        def run_load():
            headers, response = full_url.request(self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)
            return response
        if not isasync:
            return run_load()
        else:
            threading.Thread(target=run_load).start()

    def dispatch_xhr_onload(self, out, handle):
        if self.discarded: return
        self.tab.browser.measure.time('evaljs xhr_onload')
        do_default = self.interp.evaljs(XHR_ONLOAD_JS, out=out, handle=handle)
        self.tab.browser.measure.stop('evaljs xhr_onload')

    def dispatch_settimeout(self, handle):
        if self.discarded: return
        self.interp.evaljs(SETTIMEOUT_JS, handle=handle)

    def setTimeout(self, handle, time):
        def run_callback():
            task = Task(self.dispatch_settimeout, handle)
            self.tab.task_runner.schedule_task(task)
        threading.Timer(time / 1000.0, run_callback).start()

    def requestAnimationFrame(self):
        self.tab.browser.set_needs_animation_frame(self.tab)