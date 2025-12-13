from htds.dataset.service.sdk import *
import re

def _handle_params(key, value):
    operator_list = [">", "<", ">=", "<=", "!=", "<>"]
    if isinstance(value, str):
        try:
            operator = re.match(r'[><=!]+', value).group()
        except:
            operator = None
        if operator in operator_list:
            where_str = key + " " + value[:len(operator)] + "'"+value[len(operator):]+"'"
        elif value.lower().strip() == "is not null" or value.lower().strip() == "is null":
            where_str = key + " " + value
        elif value.strip()[:4] == "like":
            where_str = key + " " + value
        else:
            if 'date_format' in value:
                value = "(" + value + ")"
            else:
                value = "(" + "'" + value + "'" + ")"
            where_str = key + " " + "in" + " " + value
    elif isinstance(value, int) or isinstance(value, float):
        value = "(" + str(value) + ")"
        where_str = key + " " + "in" + " " + value
    elif isinstance(value, list):
        if len(value) == 0:
            where_str = ""
        elif len(value) == 1:
            p_value = value[0]
            if isinstance(p_value, str):
                try:
                    operator = re.match(r'[><=!]+', p_value).group()
                except:
                    operator = None
                if operator in operator_list:
                    where_str = key + " " + p_value[:len(operator)] + "'"+p_value[len(operator):]+"'"
                elif p_value.lower().strip() == "is not null" or p_value.lower().strip() == "is null":
                    where_str = key + " " + p_value
                elif p_value.strip()[:4] == "like":
                    where_str = key + " " + p_value
                else:
                    if 'date_format' in p_value:
                        p_value = "(" + p_value + ")"
                    else:
                        p_value = "(" + "'" + p_value + "'" + ")"
                    where_str = key + " " + "in" + " " + p_value
            elif isinstance(p_value, int) or isinstance(p_value, float):
                p_value = "(" + str(p_value) + ")"
                where_str = key + " " + "in" + " " + p_value
        else:
            compare_oprator = 0
            for i in value:
                if isinstance(i, str):
                    i = i.strip()
                if isinstance(i, str) and (i[0] in operator_list or i[:2] in operator_list):
                    compare_oprator += 1
            if compare_oprator == 0:
                value_str = str(tuple(value))
                where_str = key + " " + "in" + " " + value_str
            else:
                where_str = ""
                value_num = len(value)
                for i in range(value_num):
                    try:
                        v = value[i].strip()
                        operator = re.match(r'[><=!]+', v).group()
                        if not where_str:
                            where_str += key + " " + v[:len(operator)] + "'"+v[len(operator):]+"'"
                        else:
                            where_str += " " + "and" + " " + key + " " + v[:len(operator)] + "'"+v[len(operator):]+"'"
                    except Exception as e:
                        raise Exception("{0}--{1}--{2}".format(key, value[i], e))
    else:
        raise Exception("条件参数的值，仅支持单个值 或多个值的列表，请重新输入！")
    return where_str


def get_hive_data(library_name, **kwargs):
    ds_name = "dw-bigdata-hive"
    if "." not in library_name:
        raise Exception("library_name格式为 scheme+'.'+表名，如：SRC_CENTER_ADMIN.stk_blocktrade")
    factor_fields = ""
    where_str = ""
    limit_str = ""
    for key in kwargs:
        if key == "factors":
            factor_cols = kwargs["factors"]
            if isinstance(factor_cols, str):
                factor_cols = [factor_cols]
            elif isinstance(factor_cols, list):
                factor_cols = factor_cols
            else:
                raise Exception("factors为单个列名或多个列名的列表！")
            factor_fields = ",".join(factor_cols)
        elif key == "limit":
            pass
        else:
            if not where_str:
                where_str += " " + _handle_params(key, kwargs[key])
            else:
                where_str += " " + "and" + " " + _handle_params(key, kwargs[key])
    if "limit" in kwargs:
        row_num = kwargs["limit"]
        limit_str = " " + f"limit {row_num}"
    if not factor_fields:
        columns = "*"
    else:
        columns = factor_fields
    if where_str:
        where_str = "where" + " " + where_str
    if limit_str:
        sql_use = "select {0} from {1} {2} {3}".format(columns, library_name, where_str, limit_str)
    else:
        sql_use = "select {0} from {1} {2}".format(columns, library_name, where_str)
    print(sql_use)
    htdsc = HTDSContext()
    sql_execute = htdsc.get_public_datasource(ds_name)
    df = sql_execute.execute(sql_use, ret=True)
    return df


if __name__ == '__main__':
    API_KWARGS = {"library_name": "SRC_CENTER_ADMIN.stk_blocktrade", "tradingday": [">=2025-12-03 00:00:00","<=2025-12-03 23:59:59"]}
    # API_KWARGS = {"library_name": "SRC_CENTER_ADMIN.stk_blocktrade",
    #               "tradingday": "2025-12-03 00:00:00"}
    # API_KWARGS = {"library_name": "SRC_CENTER_ADMIN.stk_blocktrade",
    #               "limit": "10"}
    df = get_hive_data(**API_KWARGS)
    print(df)
