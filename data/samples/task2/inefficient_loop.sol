// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract LoopGas {
    uint256[] public values;

    function sum() public view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < values.length; i++) {
            total += values[i];
        }
        return total;
    }
}
