def solution(A):
    A.sort()

    value = 0

    for index, object in enumerate(A): # range(0, len(A)):

        if object > 0:
            if object - A[index - 1] > 1:
                value = A[index-1] + 1
                return value
        if object <= 0:
            value = 1

        return value

# list = [1, 3, 6, 4, 1, 2]
list = [-1, -3]
print(solution(list))

# 1, 1, 2, 3, 4, 6