from typing import Dict
from collections import OrderedDict

class Tree(object):
    """A generic tree."""
    data = None
    node_id = None
    children: OrderedDict = None

    def __init__(self, node_id, data = None, children: OrderedDict = None):
        self.node_id = node_id
        self.data = data
        
        if children is None:
            self.children = OrderedDict()
        else:
            self.children = children

    def __str__(self, indent=1):
        indent = indent
        res = str(self.node_id) + ': { '
        for child_item in self.children.values():
            res += '\n' + '\t' * indent + child_item.__str__(indent=indent+1)
        if len(self.children) > 0:
            res += '\n' + '\t' * (indent - 1) + '}'
        else:
            res += '}'
        return res

    def __repr__(self):
        return '{' + self.__str__().replace('}', '}, ') + '}'

    def get_num_direct_children(self):
        if self.children is None:
            return 0
        else:
            return len(self.children)

    def get_total_children(self):
        return self.get_num_direct_children() + sum([c.get_total_children() for c in self.children.values()])

    def get_child_ids(self):
        return list(self.children.keys())

    def get_children(self):
        return list(self.children.values())

    def get_child(self, child_id):
        return self.children.get(child_id, None)

    def add_child(self, child_id, entry):
        if isinstance(entry, Tree):
            self.add_child_tree(child_id, entry)
        else:
            self.add_child_data(child_id, entry)
    
    def add_child_data(self, child_id, data):
        self.children[child_id] = Tree(node_id=child_id, data=data)

    def add_child_tree(self, child_id, tr):
        self.children[child_id] = tr

    def remove_child(self, child_id):
        return self.children.pop(child_id, None)
