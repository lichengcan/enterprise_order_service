class NumberSecret:
    """数字密码锁模拟。

    这个类把“锁”的状态放到对象属性里，而不是只放在 start() 的局部变量中。
    这样更像真实业务里的对象：它知道自己是否已打开、是否已锁定、已经输错几次。
    """

    def __init__(self, password: str = "1234", max_attempts: int = 3) -> None:
        self.password = password
        self.max_attempts = max_attempts
        self.failed_attempts = 0
        self.is_locked = False
        self.is_open = False

    def _is_valid_input(self, user_input: str) -> bool:
        """校验是否为 4 位普通数字。

        `isdigit()` 会接受部分非 ASCII 数字，比如全角数字。
        这里用 `isascii() + isdecimal()` 限制为键盘上的 0-9。
        """
        return len(user_input) == 4 and user_input.isascii() and user_input.isdecimal()

    def _remaining_attempts(self) -> int:
        """返回剩余可尝试次数。"""
        return self.max_attempts - self.failed_attempts

    def _lock(self) -> None:
        """锁定密码锁。"""
        self.is_locked = True
        print("密码错误次数过多，锁已锁定")

    def reset_attempts(self) -> None:
        """重置输错次数，并解除锁定状态。

        注意：这里不是修改密码，只是模拟管理员把锁从“锁定状态”恢复为“可继续尝试”。
        """
        self.failed_attempts = 0
        self.is_locked = False
        self.is_open = False
        print("密码锁已重置，重新获得3次机会\n")

    def try_unlock(self, user_input: str) -> bool:
        """尝试解锁。

        返回值：
        - True：密码正确，锁已打开。
        - False：密码错误、输入格式错误，或者当前已经锁定。
        """
        if self.is_locked:
            print("锁已锁定，请先重置")
            return False

        if not self._is_valid_input(user_input):
            print("请输入四位数字密码")
            return False

        if user_input == self.password:
            self.is_open = True
            self.failed_attempts = 0
            print("密码正确，锁已打开")
            return True

        self.failed_attempts += 1
        remaining = self._remaining_attempts()
        if remaining > 0:
            print(f"密码错误，剩余{remaining}次机会")
        else:
            self._lock()
        return False

    def _ask_reset(self) -> bool:
        """询问是否重置锁定状态。"""
        while True:
            answer = input("是否重置密码锁？(y/n): ").strip().lower()
            if answer == "y":
                return True
            if answer == "n":
                return False
            print("请输入 y 或 n")

    def start(self) -> None:
        """启动密码锁控制台程序。"""
        print("=== 数字密码锁 ===")
        print(f"请输入四位数字密码，共{self.max_attempts}次机会")

        while not self.is_open:
            if self.is_locked:
                if self._ask_reset():
                    self.reset_attempts()
                    continue

                print("退出应用")
                return

            user_input = input("请输入密码: ").strip()
            self.try_unlock(user_input)


if __name__ == "__main__":
    lock = NumberSecret()
    lock.start()
