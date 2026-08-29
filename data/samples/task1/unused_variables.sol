// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UnusedImports {
    /// @notice This contract has unused state variables
    uint256 public activeBalance;
    
    // Unused state variables
    uint256 private unusedVar1;
    bool private unusedFlag;
    address private unusedAddress;
    
    constructor() {
        activeBalance = 1000;
        // unusedVar1, unusedFlag, unusedAddress are never used
    }
    
    function getBalance() public view returns (uint256) {
        return activeBalance;
    }
}