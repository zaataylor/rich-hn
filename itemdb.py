from typing import List

from items import Item

class ItemDB(object):
    """A DB for global Item state."""
    items: dict = None

    def __init__(self, items: dict = None):
        if items is None:
            self.items = {}
        else:
            self.items = items

    def __str__(self):
        s = ''
        if self.items is not None:
            for item in self.items.values():
                s += '{} ({})\n'.format(item.get_title(), item.get_id())
        return s
    
    def add_all_items(self, items: List[Item]):
        for item in items:
            self.add_item(item)

    def add_item(self, i: Item):
        if self.items.get(i.get_id(), None) is not None:
            self.update_item(i)
        else:
            self.items[i.get_id()] = i

    def update_item(self, i: Item):
        # Use the ID of the passed in Item to locate the desired Item
        # in the items dictionary
        db_item: Item = self.items[i.get_id()]

        # Loop over the content dictionary of the passed-in Item, and
        # for each key-value pair, update the existing Item's content
        # dictionary with that data. For dictionary members of content
        # like 'kids', make sure you don't overwrite the dictionary, but
        # instead update it with the items in that dictionary. A lot of
        # the other, non-dictionary fields in content should be overwritten
        # since they might correspond to quantitative things -- like number of
        # comments or number of points -- which need to be frequently updated.
        for key, value in i.get_content().items():
            if value is not None:
                if key == 'kids':
                    db_item.content.update(value)
                else:
                    db_item.content[key] = value

