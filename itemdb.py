from items import Item

class ItemDB(object):
    """A DB for global Item state."""
    items: dict = None

    def __init__(self, items: dict = None):
        self.items = items
    
    def add_item(self, i: Item):
        if self.items.get(i.get_id(), None) is not None:
            self.update_item(i)
        else:
            self.items[i.get_id()] = i

    def update_item(self, i: Item):
        pass