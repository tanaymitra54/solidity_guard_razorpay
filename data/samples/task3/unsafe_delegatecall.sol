// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract UnsafeDelegateCall {
    address public implementation;
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    function setImplementation(address _implementation) external {
        require(msg.sender == owner, "Not owner");
        implementation = _implementation;
    }
    
    function execute(bytes calldata data) external {
        // Dangerous delegatecall without proper validation
        (bool success, ) = implementation.delegatecall(data);
        require(success, "Delegatecall failed");
    }
    
    fallback() external {
        // Unrestricted delegatecall in fallback
        implementation.delegatecall(msg.data);
    }
}