# author: Peter Okma
import xml.etree.ElementTree as Tree


class Feedback():
    """Feedback used by Alfred Script Filter

    Usage:
        fb = Feedback()
        fb.add_item('Hello', 'World')
        fb.add_item('Foo', 'Bar')
        print fb

    """

    def __init__(self):
        self.feedback = Tree.Element('items')

    def __repr__(self):
        """XML representation used by Alfred

        Returns:
            XML string
        """
        return str(Tree.tostring(self.feedback), "utf-8")

    def add_item(self, title, subtitle="", arg="", valid="yes", autocomplete="", icon="icon.png"):
        """
        Add item to alfred Feedback

        Args:
            title(str): the title displayed by Alfred
            subtitle(str):    the subtitle displayed by Alfred
            arg(str):         the value returned by alfred when item is selected
            valid(str):       whether or not the entry can be selected in Alfred to trigger an action
            autocomplete(str): the text to be inserted if an invalid item is selected.
                                This is only used if 'valid' is 'no'
            icon(str):        filename of icon that Alfred will display
        """
        item = Tree.SubElement(self.feedback, 'item', uid=str(len(self.feedback)),
                               arg=arg, valid=valid, autocomplete=autocomplete)
        _title = Tree.SubElement(item, 'title')
        _title.text = title
        _sub = Tree.SubElement(item, 'subtitle')
        _sub.text = subtitle
        _icon = Tree.SubElement(item, 'icon')
        _icon.text = icon
