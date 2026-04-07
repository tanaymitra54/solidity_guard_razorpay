// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract RandomnessVulnerability {
    mapping(address => bool) public hasWon;
    uint256 public prize = 1 ether;
    
    function playLottery() external payable {
        require(msg.value >= 0.1 ether, "Insufficient payment");
        
        // Vulnerable randomness using block properties
        uint256 randomNumber = uint256(keccak256(abi.encodePacked(
            block.timestamp,
            block.difficulty, 
            msg.sender
        ))) % 100;
        
        if (randomNumber < 10) {
            hasWon[msg.sender] = true;
            payable(msg.sender).transfer(prize);
        }
    }
    
    function getBlockHash() external view returns (bytes32) {
        // Predictable block hash usage
        return blockhash(block.number - 1);
    }
}