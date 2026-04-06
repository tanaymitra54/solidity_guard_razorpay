// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ExpensiveOperations {
    uint256[] public data;
    
    function expensiveLoop() external view returns (uint256) {
        uint256 result = 0;
        
        // Expensive operation in loop
        for (uint i = 0; i < data.length; i++) {
            result += data[i] ** 2; // Exponentiation is expensive
        }
        
        return result;
    }
    
    function stringConcatenation(string[] memory inputs) external pure returns (string memory) {
        string memory result = "";
        
        // Inefficient string concatenation in loop
        for (uint i = 0; i < inputs.length; i++) {
            result = string(abi.encodePacked(result, inputs[i]));
        }
        
        return result;
    }
}