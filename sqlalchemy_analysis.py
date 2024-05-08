from pprint import pprint
from sqlalchemy.types import Integer, String
from sqlalchemy import Table, Column, Integer, String, ForeignKey, MetaData, create_engine
from sqlalchemy.sql import select, insert, join, asc, case, true, false
from sqlalchemy.sql.selectable import Join, Subquery, Alias
from sqlalchemy.sql.elements import Label, Case

# SQLiteデータベースへの接続を設定（ここではメモリ内データベースを使用）
engine = create_engine('sqlite:///:memory:')
metadata = MetaData()

# テーブル定義
user = Table('user', metadata,
             Column('id', Integer, primary_key=True),
             Column('name', String),
             Column('email', String)
)

post = Table('post', metadata,
             Column('id', Integer, primary_key=True),
             Column('user_id', Integer, ForeignKey('user.id')),
             Column('title', String),
             Column('content', String)
)

tag = Table('tag', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String)
)

post_tag = Table('post_tag', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('post_id', Integer, ForeignKey('post.id')),
                 Column('tag_id', Integer, ForeignKey('tag.id'))
)

# メタデータを使用してテーブルをデータベースに作成
metadata.create_all(engine)
with engine.connect() as conn:
    # ユーザーデータの挿入
    conn.execute(user.insert(), [
        {'name': 'Alice', 'email': 'alice@example.com'},
        {'name': 'Bob', 'email': 'bob@example.com'}
    ])

    # 投稿データの挿入
    conn.execute(post.insert(), [
        {'user_id': 1, 'title': 'First Post', 'content': 'This is the first post.'},
        {'user_id': 1, 'title': 'Second Post', 'content': 'This is the second post.'},
        {'user_id': 2, 'title': 'Bob\'s Post', 'content': 'This is Bob\'s post.'}
    ])

    # タグデータの挿入
    conn.execute(tag.insert(), [
        {'name': 'Python'},
        {'name': 'SQLAlchemy'},
        {'name': 'Tutorial'}
    ])

    # PostTagデータの挿入（中間テーブル）
    conn.execute(post_tag.insert(), [
        {'post_id': 1, 'tag_id': 1},
        {'post_id': 1, 'tag_id': 2},
        {'post_id': 2, 'tag_id': 3},
        {'post_id': 3, 'tag_id': 2}
    ])
    
    print('-----------')
    stmt = select(user)
    pprint(vars(stmt))
    result = conn.execute(stmt)
    print([row for row in result])
    print('-----------')
    stmt = select(post)
    result = conn.execute(stmt)
    print([row for row in result])
    print('-----------')
    stmt = select(tag)
    result = conn.execute(stmt)
    print([row for row in result])
    print('-----------')
    stmt = select(post_tag)
    result = conn.execute(stmt)
    print([row for row in result])
    print('-----------')

built_in_function_dict = {
    '<built-in function eq>': '=',
    '<built-in function ne>': '!='
}

def get_case_info(case_statement):
    if type(case_statement) is Case:
        print('-----------')
        print(type(case_statement))
        pprint(vars(case_statement))
        pprint(vars(case_statement.whens[0][0]))
        pprint(vars(case_statement.whens[0][0].element))
        return {
            'left': get_column_info(case_statement.whens[0][0].element.left),
            'right': get_column_info(case_statement.whens[0][0].element.right),
            'operator': built_in_function_dict[str(case_statement.whens[0][0].element.operator)]
        }

def get_column_info(column):
    if type(column) is Column:
        return {
            'name': column.name,
            'table': get_table_info(column.table)
        }
    elif type(column) is Label:
        return {
            **get_column_info(column.element),
            'label': column.name
        }
    elif type(column) is Case:
        return get_case_info(column)

    else:
        print('-----------')
        print(type(column))
        pprint(vars(column))
        raise Exception
    
def get_table_info(table):
    if type(table) is Table:
        return {
            'name': table.fullname,
            'schema': table.schema
        }
    elif type(table) is Subquery:
        return {'name': 'sub_statement'}
    elif type(table) is Alias:
        return get_table_info(table.element)
    else:
        print('-----------')
        print(type(table))
        pprint(vars(table))
        raise Exception
        

def get_from_table_list(froms):
    if type(froms) is Join:
        right_table = {
            **get_table_info(froms.right),
            'is_outer': froms.isouter,
            'onclause': {
                'left': get_column_info(froms.onclause.left),
                'right': get_column_info(froms.onclause.right),
                'operator': built_in_function_dict[str(froms.onclause.operator)]
            }
        }
        return [*get_from_table_list(froms.left), right_table]
    else:
        return [get_table_info(froms)]

post_tag_a = post_tag.alias('post_tagn')

sub_stmt = select(
    tag.c.id,
    tag.c.name
).select_from(
    tag
).where(
    post_tag_a.c.tag_id == tag.c.id
)
stmt = select(
    user.c.id.label('hoge'),
    user.c.name,
    user.c.email,
    post.c.id,
    sub_stmt.c.id,
    sub_stmt.c.name,
    case(
        (sub_stmt.c.id == sub_stmt.c.name, sub_stmt.c.id),
        (sub_stmt.c.id != sub_stmt.c.name, sub_stmt.c.name),
        else_=sub_stmt.c.id
    ).label('is_hoge')
).select_from(
    user.join(
        post,
        onclause=user.c.id == post.c.user_id
    ).outerjoin(
        post_tag_a,
        onclause=post.c.id == post_tag_a.c.post_id
    ).outerjoin(
        sub_stmt,
        onclause=post_tag_a.c.tag_id == sub_stmt.c.id
    )
).order_by(asc(user.c.id))
pprint(vars(stmt))
print('-----------')
pprint([get_column_info(column) for column in stmt.selected_columns])
pprint(get_from_table_list(stmt.froms[0]))
pprint(stmt._order_by_clauses[0])
pprint(vars(stmt._order_by_clauses[0]))
