"""
This is a rdflib plugin for parsing Hextuple files, which are Newline-Delimited JSON
(ndjson) files, into Conjunctive. The store that backs the graph *must* be able to
handle contexts, i.e. multiple graphs.
"""
from __future__ import annotations

import json
import warnings
from typing import TYPE_CHECKING, Any, List, Optional, Union

from rdflib.graph import ConjunctiveGraph, Graph
from rdflib.parser import FileInputSource, InputSource, Parser
from rdflib.term import BNode, Literal, URIRef

__all__ = ["HextuplesParser"]


class HextuplesParser(Parser):
    """
    An RDFLib parser for Hextuples

    """

    def __init__(self):
        pass

    def _load_json_line(self, line: str) -> List[Optional[Any]]:
        # this complex handing is because the 'value' component is
        # allowed to be "" but not None
        # all other "" values are treated as None
        ret1 = json.loads(line)
        ret2 = [x if x != "" else None for x in ret1]
        if ret1[2] == "":
            ret2[2] = ""
        return ret2

    def _parse_hextuple(
        self, cg: ConjunctiveGraph, tup: List[Union[str, None]]
    ) -> None:
        # all values check
        # subject, predicate, value, datatype cannot be None
        # language and graph may be None
        if tup[0] is None or tup[1] is None or tup[2] is None or tup[3] is None:
            raise ValueError(
                "subject, predicate, value, datatype cannot be None. Given: " f"{tup}"
            )

        # 1 - subject
        s: Union[URIRef, BNode]
        if tup[0].startswith("_"):
            s = BNode(value=tup[0].replace("_:", ""))
        else:
            s = URIRef(tup[0])

        # 2 - predicate
        p = URIRef(tup[1])

        # 3 - value
        o: Union[URIRef, BNode, Literal]
        if tup[3] == "globalId":
            o = URIRef(tup[2])
        elif tup[3] == "localId":
            o = BNode(value=tup[2].replace("_:", ""))
        else:  # literal
            if tup[4] is None:
                o = Literal(tup[2], datatype=URIRef(tup[3]))
            else:
                o = Literal(tup[2], lang=tup[4])

        # 6 - context
        if tup[5] is not None:
            c = URIRef(tup[5])
            # type error: Argument 1 to "add" of "ConjunctiveGraph" has incompatible type "Tuple[Union[URIRef, BNode], URIRef, Union[URIRef, BNode, Literal], URIRef]"; expected "Union[Tuple[Node, Node, Node], Tuple[Node, Node, Node, Optional[Graph]]]"
            cg.add((s, p, o, c))  # type: ignore[arg-type]
        else:
            cg.add((s, p, o))

    # type error: Signature of "parse" incompatible with supertype "Parser"
    def parse(self, source: InputSource, graph: Graph, **kwargs: Any) -> None:  # type: ignore[override]
        if kwargs.get("encoding") not in [None, "utf-8"]:
            warnings.warn(
                f"Hextuples files are always utf-8 encoded, "
                f"I was passed: {kwargs.get('encoding')}, "
                "but I'm still going to use utf-8"
            )

        assert (
            graph.store.context_aware
        ), "Hextuples Parser needs a context-aware store!"

        cg = ConjunctiveGraph(store=graph.store, identifier=graph.identifier)
        cg.default_context = graph

        # handle different source types - only file and string (data) for now
        if hasattr(source, "file"):
            if TYPE_CHECKING:
                assert isinstance(source, FileInputSource)
            # type error: Item "TextIOBase" of "Union[BinaryIO, TextIO, TextIOBase, RawIOBase, BufferedIOBase]" has no attribute "name"
            # type error: Item "RawIOBase" of "Union[BinaryIO, TextIO, TextIOBase, RawIOBase, BufferedIOBase]" has no attribute "name"
            # type error: Item "BufferedIOBase" of "Union[BinaryIO, TextIO, TextIOBase, RawIOBase, BufferedIOBase]" has no attribute "name"
            with open(source.file.name, encoding="utf-8") as fp:  # type: ignore[union-attr]
                for l in fp:  # noqa: E741
                    self._parse_hextuple(cg, self._load_json_line(l))
        elif hasattr(source, "_InputSource__bytefile"):
            if hasattr(source._InputSource__bytefile, "wrapped"):
                for (
                    l  # noqa: E741
                ) in source._InputSource__bytefile.wrapped.strip().splitlines():
                    self._parse_hextuple(cg, self._load_json_line(l))
