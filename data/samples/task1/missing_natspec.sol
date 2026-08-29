// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

contract NoNatSpec {
    uint256 public total;

    function add(uint256 value) public {
        total += value;
    }
}
