package aws.apigateway.logging

import rego.v1

# ----------------------------------------------------------------------------------------------
# Valid Tests
# ----------------------------------------------------------------------------------------------

test_valid_log_level if {
  result = deny with input.plan as data.mock.valid.log_level
  result == []
}

# ----------------------------------------------------------------------------------------------
# Invalid Tests
# ----------------------------------------------------------------------------------------------

test_log_level_invalid if {
  result = deny with input.plan as data.mock.invalid.log_level
  count(result) == 1
  result[0].decision == "fail"
  count(result[0].violations) == 1
}

test_log_level_undefined if {
  result = deny with input.plan as data.mock.invalid.undefined_log_level
  count(result) == 1
  result[0].decision == "fail"
  count(result[0].violations) == 1
}

test_method_setting_undefined if {
  result = deny with input.plan as data.mock.invalid.undefined_method_settings
  count(result) == 1
  result[0].decision == "fail"
  count(result[0].violations) == 1
}
