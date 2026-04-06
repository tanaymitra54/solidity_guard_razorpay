// SPDX-License-Identifier: MIT
pragma solidity 0.4.25;

contract OldPragma {
    uint public balance;
    
    // @dev Old function without NatSpec
    function getBalance() public view returns (uint) {
        return balance;
    }
    
    function OldPragma() public {
        balance = 100;
    }
}