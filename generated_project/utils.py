def print_first_n_numbers(n: int) -> None:
    if n <= 0:
        return
    else:
        for i in range(n):
            print(i + 1, end=" ")

