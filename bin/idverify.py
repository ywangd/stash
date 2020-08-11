def a():
    ID = input('请输入十八位身份证号码: ')
    if len(ID) != 18:
        print("错误的身份证号码")
        print("请重新输入！")
        a()
    else:
        print("你的身份证号码是 " + ID)
        ID_check = ID[17]
        W = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        ID_num = [18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        ID_CHECK = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        ID_aXw = 0
        for i in range(len(W)):
            ID_aXw = ID_aXw + int(ID[i]) * W[i]
        ID_Check = ID_aXw % 11
        if ID_check != ID_CHECK[ID_Check]:
            print('错误的身份证号码')
            a()
        else:
            print('正确的身份证号码')
            ID_add = ID[0:6]
            ID_birth = ID[6:14]
            ID_sex = ID[14:17]
            year = ID_birth[0:4]
            month = ID_birth[4:6]
            day = ID_birth[6:8]
            print("生日: " + year + '年' + month + '月' + day + '日')
            if int(ID_sex) % 2 == 0:
                print('性别：女')
            else:
                print('性别：男')
if __name__ == "__main__":
    a()
