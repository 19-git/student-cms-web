"""
该文件用于记录 学生类，学生的属性信息为：姓名，性别，年龄，手机号，描述信息，
"""

class Student:
    def __init__(self,name,gender,age,phone,desc):

        """
        该魔法方法，用于初始化 属性信息，
        ：param name: 学生信息

        """

        self.name = name
        self.gender =gender
        self.age = age
        self.phone = phone
        self.desc = desc

    def __str__(self):
        return f'学生姓名：{self.name}，性别：{self.gender} ，年龄：{self.age}， 电话：{self.phone}， 描述信息：{self.desc} '

if __name__ == '__main__':
    s = Student("杨子宇","男",19,12345678901,"好人")
    print(s)