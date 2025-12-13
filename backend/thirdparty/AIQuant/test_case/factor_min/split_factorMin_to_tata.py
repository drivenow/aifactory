import pandas as pd
import os


def get_Monthly_Data(
        factor_complete_path="/dfs/user/quanttest007/library/l3_data/l3_factor/research/python/1MIN/factor/",
        start_month=202401, end_month=202511,
        save_path="/dfs/group/800657"):
    """
    Args:
        factor_complete_path: 因子文件夹路径
        save_path: 保存路径
        start_month: 开始月份，格式为YYYYMM（整数或字符串）
        end_month: 结束月份，格式为YYYYMM（整数或字符串）
    """

    # 获取所有以.SZ结尾的目录
    def find_sz_directories(path):
        """
        Args:
            path: 要搜索的根路径

        Returns:
            list: 包含完整路径的目录列表
        """
        sz_dirs = []

        # 检查路径是否存在
        if not os.path.exists(path):
            print(f"路径不存在: {path}")
            return sz_dirs

        # 遍历路径下的所有项目
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            # 检查是否是目录且以 .SH 结尾
            if os.path.isdir(item_path) and item.endswith('.SH'):
                sz_dirs.append(item)
        return sz_dirs

    # 获取时间
    def get_months_between(start_month, end_month):
        """
        获取两个月份之间的所有月份列表

        Args:
            start_month: 开始月份，格式为YYYYMM（整数或字符串）
            end_month: 结束月份，格式为YYYYMM（整数或字符串）

        Returns:
            list: 月份列表，格式为['YYYYMM', ...]
        """
        # 转换为字符串并确保格式正确
        start_str = str(start_month)
        end_str = str(end_month)

        # 转换为日期（每月的第一天）
        start_date = pd.to_datetime(start_str, format='%Y%m')
        print(start_date)
        end_date = pd.to_datetime(end_str, format='%Y%m')

        # 生成月份范围
        months_start_range = pd.date_range(start=start_date, end=end_date, freq='MS')
        print(months_start_range)
        months_start_range = [d.strftime('%Y%m%d') for d in months_start_range]

        end_date = end_date + pd.DateOffset(months=1)  # 加一个月

        months_end_range = pd.date_range(start=start_date, end=end_date, freq='ME')
        print(months_end_range)
        months_end_range = [d.strftime('%Y%m%d') for d in months_end_range]
        # 格式化为YYYYMMDD
        months_list = list(zip(months_start_range, months_end_range))
        # months_list = [(d.strftime('%Y%m%d'),d.strftime('%Y%m%d')) for d in months_list]

        return months_list

    # 使用示例

    symbol_list = find_sz_directories(
        path=factor_complete_path)
    months_list = get_months_between(start_month=start_month, end_month=end_month)

    # 从factor_path中提取l3_factor后面的部分作为library参数
    if '/l3_factor/' in factor_complete_path:
        library_name = factor_complete_path.split('/l3_factor')[1]
    else:
        library_name = factor_complete_path  # 如果没有找到l3_factor，则使用完整路径

    # 得到fl对象
    from L3FactorFrame.FactorLibManager import FactorLib
    fl = FactorLib()
    # 遍历每个月份
    for month in months_list:
        # 遍历每个因子
        df_list = []  # 保存每个月份的所有因子数据
        for symbol in symbol_list:
            try:
                factor_df = fl.load_factor_data(library=library_name, symbols=symbol, start_date=month[0],
                                                end_date=month[1])
                data = factor_df.to_pandas()
                # 将格式改一下
                data['datetime'] = pd.to_datetime(data['DateTime'])
                data['datetime'] = data['datetime'].dt.strftime('%Y%m%d')
                data.rename(columns={'DateTime': 'data', 'Symbol': 'symbol'}, inplace=True)
                data = data.reindex(
                    columns=['datetime', 'symbol'] + [col for col in data.columns if col not in ['datetime', 'symbol']])
                df_list.append(data)
            except Exception as e:
                print(f"fl调用时出现了异常：{e}\n")

        if len(df_list) > 0:
            df = pd.concat(df_list, axis=0)
            # 保存每个月份的所有因子数据
            temp_month = month[0][:6]
            if not os.path.exists(f"{save_path}/{temp_month}"):
                print(f"创建目录: {save_path}/{temp_month}\n")
                os.makedirs(f"{save_path}/{temp_month}")
            try:
                df.to_parquet(f"{save_path}/{temp_month}/Factormin.parquet")
            except:
                print(f"保存为parquet格式时出现异常\n")


if __name__ == '__main__':
    # /dfs/group/800657/library_alpha/quant_data/factor/daily_factor/
    temp_factor_compelte_path="/data/user/quanttest007/library/l3_data/l3_factor/research/python/1MIN/factor"
    temp_sava_path="/dfs/group/800657/save_path/"
    get_Monthly_Data(factor_complete_path=temp_factor_compelte_path,save_path=temp_sava_path)

