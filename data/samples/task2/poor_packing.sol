// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract PackingIssues {
    // Poor struct packing - wastes storage slots
    struct User {
        bool isActive;      // 1 byte
        uint256 balance;    // 32 bytes  
        bool isVerified;    // 1 byte
        uint256 timestamp;  // 32 bytes
        uint8 level;        // 1 byte
    }
    
    User[] public users;
    
    function addUser(uint256 balance, uint8 level) external {
        users.push(User({
            isActive: true,
            balance: balance,
            isVerified: false, 
            timestamp: block.timestamp,
            level: level
        }));
    }
}