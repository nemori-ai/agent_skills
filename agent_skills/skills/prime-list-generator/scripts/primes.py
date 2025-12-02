import sys


def sieve_primes(n: int):
    if n <= 2:
        return []
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p < n:
        if is_prime[p]:
            step = p
            start = p * p
            is_prime[start:n:step] = [False] * len(is_prime[start:n:step])
        p += 1
    return [i for i, prime in enumerate(is_prime) if prime]


def main(argv):
    if len(argv) != 2:
        print("Usage: python primes.py <n>")
        return 1
    arg = argv[1]
    try:
        n = int(arg)
    except ValueError:
        print(f"Error: n must be an integer, got '{arg}'")
        return 1

    if n <= 2:
        print("# no primes less than 2")
        return 0

    primes = sieve_primes(n)
    print(" ".join(str(p) for p in primes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
