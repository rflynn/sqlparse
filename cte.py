
import sys
sys.path.append('.')

try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO

import sqlparse
from sqlparse import tokens as T
from sqlparse.sql import Comment, Identifier, IdentifierList, Statement
from sqlparse.utils import imt

from copy import copy, deepcopy


def dump2str(stmt):
    output = StringIO()
    stmt._pprint_tree(f=output)
    return output.getvalue()

def f(t):
    return not (t.is_whitespace()
                or imt(t, t=T.Comment, i=Comment))

def test_normalize_whitespace_and_comments():
    sql = 'with foo as (select 1) select 1 /* multi */\n-- single'
    stmt = sqlparse.parse(sql)[0]
    norm = stmt._filter_tree(f)
    assert dump2str(norm) == \
'''\
 0 CTE 'with'
 1 Identifier 'fooas(...'
 |  0 Name 'foo'
 |  1 Keyword 'as'
 |  2 Parenthesis '(selec...'
 |  |  0 Punctuation '('
 |  |  1 DML 'select'
 |  |  2 Integer '1'
 |  |  3 Punctuation ')'
 2 DML 'select'
 3 Integer '1'
'''


class NormalizedStatement(Statement):

    def __init__(self, stmt):
        #self.stmt_orig = stmt
        #self.stmt = copy())
        norm_stmt = stmt._filter_tree(NormalizedStatement.ws_or_comment)
        super(NormalizedStatement, self).__init__(norm_stmt)

    @staticmethod
    def ws_or_comment(token):
        return not (token.is_whitespace()
            or imt(token, t=T.Comment, i=Comment))


class CTEStmt(object):

    def __init__(self, stmt):
        if stmt[0].ttype != T.CTE:
            raise TypeError
        self.stmt_orig = stmt
        self.stmt = NormalizedStatement(stmt)
        self.recursive = None
        self.query_list = None
        self.select = None
        self._parse()

    def __repr__(self):
        return '<CTEStmt queries={} select={}>'.format(
            list(self.queries()), list(self.select))

    def queries(self):
        return iter(s for s in self.query_list or []
                        if CTEStmt.is_cte_subquery(s))

    def query_count(self):
        return len(list(self.queries()))

    def thru_query(self, n):

        # figure out which index the query is
        qis = [i for i, s in enumerate(self.query_list or [])
                        if CTEStmt.is_cte_subquery(s)]
        qi = qis[n]

        # reconstruct tokenlist for a modified CTE...
        tokens = self.stmt[0:1] # with
        if self.recursive:
            tokens.append(self.recursive)
        # ...containing only queries thru N
        tokens.extend(self.query_list[:qi+1])
        tokens.extend(self.select)
        stmtcopy = self.stmt_orig.__class__(tokens)

        return stmtcopy

    def _parse(self):
        stmts = iter(enumerate(self.stmt))
        next(stmts) # skip 'WITH'...
        i, s = next(stmts)
        # import pdb; pdb.set_trace()
        if s.ttype == T.Keyword and s.normalized == 'RECURSIVE':
            self.recursive = s
            i, s = next(stmts)
        if isinstance(s, IdentifierList):
            self.query_list = s
            i, s = next(stmts)
        if s.ttype == T.Keyword.DML:
            self.select = self.stmt[i:]
            i, s = next(stmts)

    @staticmethod
    def is_cte_subquery(node):
        return (isinstance(node, Identifier)
            and node[0].ttype == T.Name
            and node[1].ttype == T.Keyword
            and node[1].normalized == 'AS')


def cte_query_list(stmt):
    '''given a CTE, list all the query names'''
    stmt = stmt._filter_tree(f)
    query_names = []
    if stmt[0].ttype != T.CTE:
        raise TypeError
    li = 1
    if stmt[1].ttype == T.Keyword and stmt[1].normalized == 'RECURSIVE':
        li += 1
    if stmt[li].is_group() and isinstance(stmt[li], IdentifierList):
        subqs = [x for x in stmt[li] if is_cte_subquery(x)]
        query_names = [x[0].value for x in subqs]
    return query_names

def cte_parse2list(sql):
    stmt = sqlparse.parse(sql)[0]
    return cte_query_list(stmt)

def test_cte_list1():
    sql = 'with foo as (select 1), bar as (select 2) select 3'
    assert cte_parse2list(sql) == ['foo', 'bar']

def test_cte_list_recursive():
    sql = 'with recursive foo as (select 1), bar as (select 2) select 3'
    assert cte_parse2list(sql) == ['foo', 'bar']

if __name__ == '__main__':

    from pprint import pprint

    sql = 'with recursive foo as (select 1), bar as (select 2) select 3'
    stmt = sqlparse.parse(sql)[0]
    stmt = stmt._filter_tree(f)
    stmt._pprint_tree()

    c = CTEStmt(stmt)
    print(c)

    for i in range(c.query_count()):
        print(i)
        c.thru_query(i)._pprint_tree()

    #pprint(cte_query_list(stmt))
