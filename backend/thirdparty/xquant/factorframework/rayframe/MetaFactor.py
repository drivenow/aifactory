import re


class MetaBaseFactor(type):
    def __new__(cls, name, bases, attrs):
        """
        attrs: 用户定义的参数
        类改名，按用户定义的方式
        """
        if name in ["HFBaseFactor", "Factor"]:
            return type.__new__(cls, name, bases, attrs)

        for k, v in attrs.items():
            # 保存类属性和列的映射关系到mappings字典
            if k == "custom_params":
                for subk, subv in attrs["custom_params"].items():
                    assert type(subv) == int or type(subv) == str, "参数{}类型错误：custom_params只支持传入str或者int类型的参数！".format(
                        subk)
                    if type(subv) == str:
                        assert not re.search(r"\W", subv), "参数{}值错误: custom_params只支持传入值为大小写字母、数字或下划线组合的值！".format(subk)

        mapping_name_func = getattr(bases[0], "mapping_name_func", lambda x, y: x)  # 获取高频因子基类中的类命名函数
        if "custom_params" in attrs:
            new_name = mapping_name_func(bases[0], name, attrs["custom_params"])
        else:
            new_name = name
        instance = super(MetaBaseFactor, cls).__new__(cls, new_name, bases, attrs)
        output_factor_names = getattr(instance, 'output_factor_names')
        output_factor_names = [i.replace(name, new_name) for i in output_factor_names]
        setattr(instance, "output_factor_names", output_factor_names)
        for k, v in attrs.items():
            # 覆盖原始因子类中的参数，比如security_type或securities
            if k != "custom_params":
                if attrs['factor_type'] == "DAY":
                    if k not in ["data_input_mode", "None"]:
                        print("注意：当前正在修改基础因子类的默认类属性{}：{}!".format(k, v))
                        setattr(instance, k, v)
                else:
                    if k not in ["depend_factor", "day_lag", "quarter_lag"]:
                        print("注意：当前正在修改基础因子类的默认类属性{}：{}!".format(k, v))
                        setattr(instance, k, v)
        return instance
