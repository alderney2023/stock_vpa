"""周线数据计算模块 - 从日K聚合计算周K"""
import pandas as pd


def calc_weekly(df_daily: pd.DataFrame, weeks: int = 52) -> pd.DataFrame:
    """
    从日K数据计算周K数据。

    规则：
    - 只使用完整周的数据（本周若未结束，则丢弃）
    - 周一开盘价 = 本周第一个交易日的开盘价
    - 周五收盘价 = 本周最后一个交易日的收盘价
    - 周内最高/最低 = 本周所有交易日的最高/最低
    - 成交量/成交额 = 本周所有交易日的总和

    Args:
        df_daily: 日K DataFrame，必须包含列：date, open, high, low, close, volume, amount
        weeks: 返回最近多少周的完整数据

    Returns:
        周K DataFrame，包含列：week_start, open, high, low, close, volume, amount
    """
    df = df_daily.copy()

    # 确保 date 列是 datetime
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 获取星期几（周一=0，周日=6）
    df['weekday'] = df['date'].dt.dayofweek

    # 标记每个交易日所属周的周一日期
    df['week_start'] = df['date'] - pd.to_timedelta(df['weekday'], unit='d')

    # 按周聚合
    weekly = df.groupby('week_start').agg({
        'open': 'first',      # 周一的开盘价
        'high': 'max',        # 周内最高
        'low': 'min',         # 周内最低
        'close': 'last',      # 周五的收盘价
        'volume': 'sum',      # 成交量合计
        'amount': 'sum',      # 成交额合计
    }).reset_index()

    # 只保留完整周（该周的最后一个交易日必须是周五）
    def _is_complete_week(week_start, df_source):
        """检查该周是否完整（有周五的数据）"""
        week_end = week_start + pd.Timedelta(days=4)  # 周五
        return df_source[df_source['date'] == week_end].shape[0] > 0

    # 过滤：只保留完整周
    weekly['is_complete'] = weekly['week_start'].apply(
        lambda x: _is_complete_week(x, df)
    )
    weekly = weekly[weekly['is_complete']].drop(columns=['is_complete'])

    # 取最近 N 周
    weekly = weekly.sort_values('week_start').tail(weeks).reset_index(drop=True)

    # 格式化输出
    weekly['week_start'] = weekly['week_start'].dt.strftime('%Y-%m-%d')

    return weekly
