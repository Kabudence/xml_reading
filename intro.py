def is_palindrome(word):
    word_without_spaces = word.replace(" ", "")
    palindrome = word_without_spaces[::-1]
    return palindrome == word_without_spaces


print(is_palindrome("h o l a"))