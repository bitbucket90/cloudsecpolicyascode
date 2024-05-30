package aws.apigateway.encryption

import rego.v1

# ----------------------------------------------------------------------------------------------
# Valid test cases
# ----------------------------------------------------------------------------------------------

test_valid_cache_encrypted if {
  result = deny with input.plan as data.mock.valid.cache_encrypted
  result == []
}

# ----------------------------------------------------------------------------------------------
# Invalid test cases
# ----------------------------------------------------------------------------------------------

test_invalid_cache_unencrypted if {
  result = deny with input.plan as data.mock.invalid.cache_unencrypted
  count(result) == 1
  result[0].decision == "fail"
  count(result[0].violations) == 1
}

test_undefined_cache_not_declared if {
  result = deny with input.plan as data.mock.invalid.undefined_cache_not_declared
  count(result) == 1
  result[0].decision == "fail"
  count(result[0].violations) == 1
}
