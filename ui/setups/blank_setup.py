# ui/setups/blank_setup.py
from ..tools.tree import UINode, UINodeName

class BlankSetup:
    def __init__(self, setup_tag: UINodeName):
        self.tag = setup_tag

    def get_setup(self) -> UINode:
        raise NotImplementedError("Subclasses must implement get_setup()")