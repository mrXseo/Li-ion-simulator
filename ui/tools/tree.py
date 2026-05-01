from enum import IntEnum, auto
from typing import Callable, TypeAlias, Dict, Any, List, overload
from ..widgets.base_widget import BaseWidget

class TreeTypes(IntEnum):
    DPG_COMPLEX_COMPONENT = auto()
    DPG_SIMPLE_COMPONENT = auto()
    WIDGET = auto()

Tag : TypeAlias = str
OtherParams : TypeAlias = Dict[str, Any]
UINodeName : TypeAlias = str
FullTag : TypeAlias = str

class UINode:
    
    def __init__(
        self,
        name : Tag,
        tree_type : TreeTypes,
        init_func : Callable[[Tag, OtherParams], Any],
        build_func : Callable[[Tag], Any] = lambda tag: ...,
        update_func : Callable[[], Any] = None,
        childrens : Dict[UINodeName, "UINode"] = None,
        **other_params,
        ):
        self.name = name 
        self.tree_type = tree_type

        self.init_func = init_func
        self.init_result = None

        self.build_func = build_func
        self.build_result = None

        self.update_func = update_func
        self.update_result = None

        self.init_params = other_params
        
        self.childrens = childrens
        if self.childrens is None:
            self.childrens = dict()
        
        self.tag : str = None
    
    def add_children(self, ui_node : "UINode") -> None:
        if ui_node.name in self.childrens:
            raise KeyError(ui_node.name,  "This name already exist in this layer.")
        self.childrens[ui_node.name] = ui_node
    
    def init(self, tag : Tag, **new_other_params) -> Any:
        self.init_params.update(new_other_params)
        self.init_result = self.init_func(tag = tag, **self.init_params)
        self.tag = tag
        return self.init_result

    def build(self, snowball_tag = '') -> Any:
        self.build_result = self.build_func(tag=snowball_tag)
        return self.build_result

    def update(self) -> Any:
        if self.update_func is None:
            return None
        self.update_result = self.update_func()
        return self.update_result

    def get_update(self) -> Any:
        if self.update_func is None:
            return self.update_func
        return self.update

class TreeParser:

    @classmethod
    def tree_init(cls, root : UINode, snowball_tag : str = '', **extra_params) -> None:
        if not extra_params:
            extra_params = dict()
        if snowball_tag:
            root.init(snowball_tag+root.name, parent = snowball_tag, **extra_params)
        else:
            root.init(snowball_tag+root.name, **extra_params)
        for child_name, child in root.childrens.items():
            TreeParser.tree_init(child, snowball_tag=snowball_tag+root.name, **extra_params)
    
    @classmethod
    def tree_build(cls, root : UINode, snowball_tag : str = '') -> None:
        root.build(snowball_tag+root.name)
        root
        for child_name, child in root.childrens.items():
            TreeParser.tree_build(child, snowball_tag=snowball_tag+root.name)

    @classmethod
    def get_update_list(cls, root : UINode) -> List[Callable]:
        update_list : List[Callable] = []
        def _get_update_list(_root : UINode):
            update_func = _root.get_update()
            if not (update_func is None):
                update_list.append(update_func)
            for child_name, child in _root.childrens.items():
                _get_update_list(child)
        _get_update_list(root)
        return update_list
    
    str_format_pipe = "│   "      # вертикальная линия для продолжения
    str_format_branch = "├── "    # узел не последний, есть братья снизу
    str_format_last = "└── "      # узел последний, ниже ничего нет
    str_format_space = "    "     # пустой отступ, когда родительская линия не рисуется

    @classmethod
    def str_format(cls, root : UINode) -> str:
        str_tree : List[str] = []
        str_tree.append(root.name)
        def _str_format(_root : UINode, tail : str = '') -> None:
            last_id = len(_root.childrens) - 1
            for child_id, child in enumerate(_root.childrens.values()):
                is_last = child_id == last_id
                tail_end = cls.str_format_branch
                apply_legasy = cls.str_format_pipe
                if is_last:
                    tail_end = cls.str_format_last
                    apply_legasy = cls.str_format_space
                str_tree.append(tail+tail_end + child.name)
                _str_format(child, tail=tail+apply_legasy)
        _str_format(root)
        return "\n".join(str_tree)

    @classmethod
    def find(
            cls, 
            root : UINode, 
            find_tag : Tag, 
            seniors_tags : List[Tag] = [], 
            last_finded_senior : int = 0, 
            trace : List[Tag] = [], 
            first : bool = True,
            strict: bool = False
        ) -> Dict[FullTag, UINode]:
        finded = dict()

        target_name = find_tag
        
        if last_finded_senior < len(seniors_tags):
            target_name = seniors_tags[last_finded_senior]
        
        if root.name == target_name:
            if not seniors_tags:
                finded["".join(trace + [root.name])] = root
                if first:
                    return finded
            for node in root.childrens.values():
                finded.update(
                    cls.find(
                        node, find_tag, seniors_tags=seniors_tags, last_finded_senior=last_finded_senior+1, trace=trace+[root.name], first=first, strict = strict
                    )
                )
                if first and finded:
                    return finded                    
        else:
            if not strict:
                last_finded_senior = 0
            for node in root.childrens.values():
                finded.update(
                    cls.find(
                        node, find_tag, seniors_tags=seniors_tags, last_finded_senior=last_finded_senior, trace=trace+[root.name], first=first, strict = strict
                    )
                )
                if first and finded:
                    return finded
        return finded


# ... после класса TreeParser добавить:
def widget_to_node(name: str, widget: BaseWidget) -> UINode:
    """
    Преобразует экземпляр BaseWidget в узел UINode.
    """
    def init_widget(tag: str, parent: str, **kwargs) -> str:
        widget.tag = tag
        widget.init(parent_tag=parent)
        return tag

    def build_widget(tag: str) -> None:
        widget.build()

    return UINode(
        name=name,
        tree_type=TreeTypes.WIDGET,
        init_func=init_widget,
        build_func=build_widget,
        update_func=widget.update
    )
