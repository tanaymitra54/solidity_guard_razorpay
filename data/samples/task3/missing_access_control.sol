// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Admin {
    mapping(address => bool) public admins;

    function setAdmin(address account, bool status) public {
        admins[account] = status;
    }
}
