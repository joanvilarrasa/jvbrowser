def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

def dpx(css_px, zoom):
    return css_px * zoom