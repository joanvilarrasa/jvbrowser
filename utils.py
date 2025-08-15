def tree_to_list(tree, list):
    list.append(tree)
    children = tree.children
    if hasattr(children, 'get'):
        children = children.get()
    for child in children:
        tree_to_list(child, list)
    return list

def dpx(css_px, zoom):
    return css_px * zoom