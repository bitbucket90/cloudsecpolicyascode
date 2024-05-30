package aws.apigateway.private_endpoints

import rego.v1

# ----------------------------------------------------------------------------------------------
# Valid test cases
# ----------------------------------------------------------------------------------------------

test_valid_create if {
  result = deny with input.plan as data.mock.valid.create
  result == []
}

# ----------------------------------------------------------------------------------------------
# Invalid test cases
# ----------------------------------------------------------------------------------------------

test_invalid_endpoint_configuration_types if {
  result := data.aws.apigateway.private_endpoints.deny with input.plan as data.mock.invalid.endpoint_configuration_types
  count(result) == 1
  result[0].decision = "fail"
  result[0].violations
  count(result[0].violations) == 1
}

test_invalid_endpoint_configuration_vpc_endpoint_ids if {
  result := data.aws.apigateway.private_endpoints.deny with input.plan as data.mock.invalid.endpoint_configuration_vpc_endpoint_ids
  count(result) == 1
  result[0].decision = "fail"
  count(result[0].violations) == 1
}
