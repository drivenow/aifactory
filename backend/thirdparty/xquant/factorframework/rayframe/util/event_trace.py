from FactorProvider.setEnv import sysFlag


def event_trace(func):
    def wrapper(*args, **kwargs):
        rst = func(*args, **kwargs)
        return rst

    return wrapper


if sysFlag == "tquant":
    from tquant.utils.event_trace import event_trace
else:
    pass
