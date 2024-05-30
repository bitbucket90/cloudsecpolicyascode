package aws.sns.no_public_access

# ----------------------------------------------------------------------------------------------
# Valid test cases
# ----------------------------------------------------------------------------------------------

test_valid_create {
    result = deny with input.plan as data.mock.valid.create
    result == []
}

test_valid_update {
    result = deny with input.plan as data.mock.valid.update
    result == []
}

# ----------------------------------------------------------------------------------------------
# Invalid test cases
# ----------------------------------------------------------------------------------------------

test_invalid_no_policy {
    result = deny with input.plan as data.mock.invalid.no_policy
    count(result) == 1
    result[0].decision == "fail"
    count(result[0].violations) == 3
}

test_invalid_bad_policy {
    result = deny with input.plan as data.mock.invalid.bad_policy
    count(result) == 1
    result[0].decision == "fail"
    count(result[0].violations) == 1
}

test_invalid_bad_multi_statement_policy {
    result = deny with input.plan as data.mock.invalid.bad_multi_statement_policy
    count(result) == 1
    result[0].decision == "fail"
    count(result[0].violations) == 1
}
