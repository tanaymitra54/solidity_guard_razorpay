// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract StorageGas {
    uint256 public price;
    uint256 public fee;

    function totalCost(uint256 quantity) public view returns (uint256) {
        uint256 cost = price * quantity;
        cost = cost + fee;
        cost = cost + fee;
        return cost;
    }
}
