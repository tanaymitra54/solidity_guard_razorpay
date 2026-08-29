// SPDX-License-Identifier: MIT
pragma solidity ^0.4.24;

contract LegacyConstructor {
    uint256 public value;

    function LegacyConstructor(uint256 initial) public {
        value = initial;
    }
}
