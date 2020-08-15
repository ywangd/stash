# -*- coding:utf-8 -*-
'''Timestamp Utilitie'''
import time
import datetime
def timestamp_to_format_time(str_time=None, format='%Y-%m-%d %H:%M:%S'): #封装函数：时间戳转换成格式化时间
    if timestamp:
        time_tuple = time.localtime(timestamp)
        result = time.strftime(format,time_tuple)
        return result
    else:
        return time.strftime(format)

print('请选择一个选项:')
n='''
            1:时间戳转换到日期
            2:日期转换到时间戳
'''
c=int(eval(input(n))) #定义菜单变量
if c == 1: #进入菜单1的判断
	print('请输入要转换的时间戳')
	timestamp=int(eval(input())) #定义需转换的时间戳,并将其转换为int整型
	print(('时间戳:',timestamp,'转换成日期格式为：',timestamp_to_format_time(timestamp)))
if c == 2:
	t='''格式:YYYY-MM-DD HH-MM-SS'''
	print(('请输入要转换的日期',t))
	a=input()
	timeStamp = int(time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
	print(timeStamp)

