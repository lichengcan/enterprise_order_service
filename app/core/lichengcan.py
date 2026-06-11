class Lichengcan:
    def __init__(self, name, age) -> None:
        self.name = name
        self.age = age
        self.hobby = "basketball"

    def say_hello(self):
        print(f"Hello, my name is {self.name}, I am {self.age} years old.")


if __name__ == "__main__":
    # 类似 Java 的 main 方法入口，直接运行此文件时执行
    person = Lichengcan("lichengcan", 18)
    person.say_hello()
    print(f"爱好: {person.hobby}")