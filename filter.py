
import sys
sys.path.append('.')

try:
    from io import StringIO
except ImportError:
    from cStringIO import StringIO

import sqlparse
from sqlparse import tokens as T
from sqlparse.sql import Comment, Identifier
from sqlparse.utils import imt


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

def cte_query_list(stmt):
    '''given a CTE, list all the query names'''
    stmt = stmt._filter_tree(f)
    query_names = []
    if stmt[0].ttype != T.CTE:
        raise TypeError
    li = 1
    if stmt[1].ttype == T.Keyword and stmt[1].normalized == 'RECURSIVE':
        li += 1
    if stmt[li].is_group():
        if stmt[li][0].__class__ == Identifier:
            if (stmt[li][0][0].ttype == T.Name and
                stmt[li][0][1].ttype == T.Keyword and
                stmt[li][0][1].normalized == 'AS'):
                query_names.append(stmt[li][0][0].value)
        qi = 1
        while qi < len(list(stmt[li])):
            if (stmt[li][qi].ttype == T.Punctuation and
                stmt[li][qi].normalized == ',' and
                stmt[li][qi+1].is_group()):
                    if (stmt[li][qi+1][0].ttype == T.Name and
                        stmt[li][qi+1][1].ttype == T.Keyword and
                        stmt[li][qi+1][1].normalized == 'AS'):
                        query_names.append(stmt[li][qi+1][0].value)
            qi += 2
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
    sql = 'with recursive foo as (select 1), bar as (select 2) select 3'
    stmt = sqlparse.parse(sql)[0]
    stmt = stmt._filter_tree(f)
    stmt._pprint_tree()
