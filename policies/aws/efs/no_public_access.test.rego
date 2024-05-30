package aws.efs.no_public_access

# ----------------------------------------------------------------------------------------------
# Valid test cases
# ----------------------------------------------------------------------------------------------
test_valid_create {
    result := deny with input.plan as data.mock.valid.create
    result == []
}

test_valid_update {
    result := deny with input.plan as data.mock.valid.update
    result == []
}

# ----------------------------------------------------------------------------------------------
# Invalid test cases
# ----------------------------------------------------------------------------------------------

test_invalid_no_policy {
    result := deny with input.plan as data.mock.invalid.no_policy
    count(result) == 1
    result[0].decision == "fail"
}

test_invalid_bad_allow_policy {
    result := deny with input.plan as data.mock.invalid.bad_allow_policy
    count(result) == 1
    result[0].decision == "fail"
}

test_invalid_bad_deny_policy {
    result := deny with input.plan as data.mock.invalid.bad_deny_policy
    count(result) == 1
    result[0].decision == "fail"
}
