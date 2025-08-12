from functools import reduce


def read_tsv(file_name):
    with open(file_name) as f:
        tsv_data = [x.strip().split('\t') for x in f.readlines()]

        # 分類のデータを除く
        return list(filter(lambda x: len(x) > 1, tsv_data))

def write_sql(file_name, sql):
    with open(file_name, mode='w') as f:
        f.write(sql)


def get_member_list(tsv_data):
    members = [x[1].split('・') for x in tsv_data]
    flat_mambers = reduce(lambda x, y: [*x, *y], members)
    return [{'id': i +1, 'name': data} for i, data in enumerate(set(flat_mambers))]


def get_group_list(tsv_data):
    return [{'id': i + 1, 'name': data} for i, data in enumerate(tsv[0] for tsv in tsv_data)]


def get_group_member(tsv_data, groups, members):
    return_value = list()
    for t in tsv_data:
        for g in groups:
            if t[0] == g['name']:
                for m in members:
                    if m['name'] in t[1].split('・'):
                        return_value.append({
                            'group_id': g['id'],
                            'member_id': m['id']
                        })
    return return_value


def create_insert_sql(table_name, data_list):
    key = data_list[0].keys()
    insert_key = ', '.join(key)
    sql = f'INSERT INTO {table_name}({insert_key}) VALUES'
    values_list = list()
    for d in data_list:
        value = list()
        for k in key:
            if type(d[k]) is str:
                value.append(f'"{d[k]}"')
            elif type(d[k]) is int:
                value.append(f'{d[k]}')
            else:
                raise Exception()
        values = ', '.join(value)
        values_list.append(f'({values})')
    return sql + ', '.join(values_list) + ';'
    


def main():
    tsv_data = read_tsv('imas.tsv')
    members = get_member_list(tsv_data)
    groups = get_group_list(tsv_data)
    group_member = get_group_member(tsv_data, groups, members)
    member_sql = create_insert_sql('members', members)
    group_sql = create_insert_sql('groups', groups)
    group_member_sql = create_insert_sql('group_member', group_member)

    sql = '\n\n'.join([group_sql, member_sql, group_member_sql])
    write_sql('imas.sql', sql)

if __name__ == '__main__':
    main()