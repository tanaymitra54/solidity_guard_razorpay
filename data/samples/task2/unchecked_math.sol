// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract InlineAssemblyGas {
    mapping(address => uint256) public balances;
    
    function inefficientTransfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Inefficient - multiple storage reads
        balances[msg.sender] = balances[msg.sender] - amount;
        balances[to] = balances[to] + amount;
        
        // Could use unchecked math since we already checked balance
    }
    
    function anotherFunction() external view returns (uint256) {
        // Reading storage in loop - should cache
        uint256 total = 0;
        for (uint i = 0; i < 10; i++) {
            total += balances[msg.sender]; // Repeated storage read
        }
        return total;
    }
}