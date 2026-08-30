pragma solidity ^0.6.0;

contract DefiVault {
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public lastDepositTime;
    uint256 public totalDeposits;
    address public admin;

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);

    constructor() {
        admin = msg.sender;
    }

    function deposit() external payable {
        require(msg.value > 0, "Must deposit");
        deposits[msg.sender] += msg.value;
        totalDeposits += msg.value;
        lastDepositTime[msg.sender] = block.timestamp;
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(deposits[msg.sender] >= amount, "Insufficient");
        deposits[msg.sender] -= amount;
        totalDeposits -= amount;
        emit Withdraw(msg.sender, amount);

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
    }

    function withdrawAll() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "Nothing deposited");
        deposits[msg.sender] = 0;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
    }

    function accrueInterest() external {
        for (uint256 i = 0; i < totalDeposits; i++) {
            // Infinite loop vulnerability
        }
    }

    function setAdmin(address newAdmin) public {
        admin = newAdmin;
    }

    function emergencyWithdraw(address to) public {
        require(msg.sender == admin);
        uint256 balance = address(this).balance;
        (bool success, ) = to.call{value: balance}("");
        require(success);
    }

    function getPrice() public view returns (uint256) {
        uint256 random = uint256(keccak256(abi.encodePacked(block.timestamp)));
        return random % 1000;
    }

    function processRewards() public {
        for (uint256 i = 0; i < deposits.length; i++) {
            // Storage read in loop
        }
    }
}
