class Member:
    def __init__(self):
        print("Member made")
    def func(self):
        print("Member class func")

class Admin(Member):
    def __init__(self):
        print("Admin made")
    def func(self):
        print("Admin class func")
gg=Member()
gg.__class__=Admin
print(gg.__class__)
print(gg.__class__.__name__.format_map.__dict__)
gg.func()
