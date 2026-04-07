// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract IntegerOverflow {
    mapping(address => uint256) public balances;
    
    constructor() {
        balances[msg.sender] = 100;
    }
    
    function transfer(address to, uint256 amount) external {
        // Potential integer overflow/underflow
        balances[msg.sender] -= amount;
        balances[to] += amount;
        
        // No checks for overflow/underflow
        // In older Solidity versions this was critical
    }
    
    function mint(address to, uint256 amount) external {
        // Potential overflow when adding
        balances[to] += amount;
    }
}