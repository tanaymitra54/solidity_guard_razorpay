// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

contract RequireString {
    function update(uint256 amount) public pure returns (uint256) {
        require(amount > 0, "amount must be positive");
        return amount;
    }
}
