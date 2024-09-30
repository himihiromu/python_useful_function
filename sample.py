
import numpy as np
N = int(input())

grid = list()

num = 0
while num < N:
    grid.append(list(map(int, list(input()))))
    num += 1

max_val = 0

grid = np.array(grid, dtype=int)

def get_series_number(array):
    sp = [i for i,n in enumerate(array) if i>0 and array[i-1]+1!=n] + [len(array)]
    ans = [array[i-1:i] for i in sp]
    return max(map(len, ans))

num = 0
while num < N:
    max_val = max(get_series_number(grid[num]), max_val)
    max_val = max(get_series_number(grid[:,num]), max_val)
    max_val = max(get_series_number(np.diag(grid, k=num)), max_val)
    max_val = max(get_series_number(np.diag(grid, k=(num * -1))), max_val)
    if N == max_val:
        break
    num += 1
print(max_val)