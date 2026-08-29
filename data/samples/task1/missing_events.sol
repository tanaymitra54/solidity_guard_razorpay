pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract NoEvents {
    address public owner;
    uint256 public totalSupply;
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
    }
    
    function updateSupply(uint256 newSupply) external {
        require(msg.sender == owner, "Not owner");
        totalSupply = newSupply;
        // Missing event emission
    }
    
    function changeOwner(address newOwner) external {
        require(msg.sender == owner, "Not owner");
        owner = newOwner;
        // Missing event emission
    }
}