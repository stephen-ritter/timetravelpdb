import timetravelpdb

x = 500

tt_pdb = timetravelpdb.TimeTravelPdb()


def add10(number):
    return number + 10


print("foo")
print("bar")
print("baz")

tt_pdb.set_trace()

y = add10(x)
x = 15
z = x + y

for i in range(15):
    print(f"THE NUMBER IS {i}")
    y = add10(i)
