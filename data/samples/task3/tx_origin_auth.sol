// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract OriginAuth {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw(uint256 amount) public {
        require(tx.origin == owner);
        payable(msg.sender).transfer(amount);
    }
}
