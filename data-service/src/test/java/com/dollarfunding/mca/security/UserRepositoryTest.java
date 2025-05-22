package com.dollarfunding.mca.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

/**
 * Test class for UserRepository that verifies the correct implementation of database access methods
 * for user information. It tests finding users by username, email, and role, as well as checking
 * username and email existence.
 */
@DataJpaTest
public class UserRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private UserRepository userRepository;

    private User operationsStaffUser;
    private User systemAdminUser;
    private User regularUser;
    
    @BeforeEach
    public void setup() {
        // Create roles
        Role operationsStaffRole = Role.createOperationsStaffRole();
        Role systemAdminRole = Role.createSystemAdminRole();
        
        // Persist roles
        entityManager.persist(operationsStaffRole);
        entityManager.persist(systemAdminRole);
        
        // Create users with different roles
        operationsStaffUser = User.builder()
                .username("ops_user")
                .password("password123")
                .email("ops@dollarfunding.com")
                .firstName("Operations")
                .lastName("User")
                .enabled(true)
                .addRole(operationsStaffRole)
                .build();
        
        systemAdminUser = User.builder()
                .username("admin_user")
                .password("password456")
                .email("admin@dollarfunding.com")
                .firstName("Admin")
                .lastName("User")
                .enabled(true)
                .addRole(systemAdminRole)
                .build();
        
        regularUser = User.builder()
                .username("regular_user")
                .password("password789")
                .email("user@dollarfunding.com")
                .firstName("Regular")
                .lastName("User")
                .enabled(true)
                .build();
        
        // Persist users
        entityManager.persist(operationsStaffUser);
        entityManager.persist(systemAdminUser);
        entityManager.persist(regularUser);
        
        entityManager.flush();
    }
    
    @Test
    @DisplayName("Test finding user by username")
    public void testFindByUsername() {
        // When
        Optional<User> foundUser = userRepository.findByUsername(operationsStaffUser.getUsername());
        
        // Then
        assertThat(foundUser).isPresent();
        assertThat(foundUser.get().getUsername()).isEqualTo(operationsStaffUser.getUsername());
        assertThat(foundUser.get().getEmail()).isEqualTo(operationsStaffUser.getEmail());
        assertThat(foundUser.get().isOperationsStaff()).isTrue();
    }
    
    @Test
    @DisplayName("Test finding user by non-existent username")
    public void testFindByNonExistentUsername() {
        // When
        Optional<User> foundUser = userRepository.findByUsername("non_existent_user");
        
        // Then
        assertThat(foundUser).isEmpty();
    }
    
    @Test
    @DisplayName("Test finding user by email")
    public void testFindByEmail() {
        // When
        Optional<User> foundUser = userRepository.findByEmail(systemAdminUser.getEmail());
        
        // Then
        assertThat(foundUser).isPresent();
        assertThat(foundUser.get().getUsername()).isEqualTo(systemAdminUser.getUsername());
        assertThat(foundUser.get().getEmail()).isEqualTo(systemAdminUser.getEmail());
        assertThat(foundUser.get().isSystemAdmin()).isTrue();
    }
    
    @Test
    @DisplayName("Test finding user by non-existent email")
    public void testFindByNonExistentEmail() {
        // When
        Optional<User> foundUser = userRepository.findByEmail("non_existent@dollarfunding.com");
        
        // Then
        assertThat(foundUser).isEmpty();
    }
    
    @Test
    @DisplayName("Test finding users by Operations Staff role")
    public void testFindOperationsStaffUsers() {
        // When
        List<User> operationsStaffUsers = userRepository.findOperationsStaffUsers();
        
        // Then
        assertThat(operationsStaffUsers).isNotEmpty();
        assertThat(operationsStaffUsers).hasSize(1);
        assertThat(operationsStaffUsers.get(0).getUsername()).isEqualTo(operationsStaffUser.getUsername());
    }
    
    @Test
    @DisplayName("Test finding users by System Admin role")
    public void testFindSystemAdminUsers() {
        // When
        List<User> systemAdminUsers = userRepository.findSystemAdminUsers();
        
        // Then
        assertThat(systemAdminUsers).isNotEmpty();
        assertThat(systemAdminUsers).hasSize(1);
        assertThat(systemAdminUsers.get(0).getUsername()).isEqualTo(systemAdminUser.getUsername());
    }
    
    @Test
    @DisplayName("Test finding users by role name")
    public void testFindByRoleName() {
        // When
        List<User> operationsStaffUsers = userRepository.findByRoleName(Role.ROLE_OPERATIONS_STAFF);
        List<User> systemAdminUsers = userRepository.findByRoleName(Role.ROLE_SYSTEM_ADMIN);
        
        // Then
        assertThat(operationsStaffUsers).isNotEmpty();
        assertThat(operationsStaffUsers).hasSize(1);
        assertThat(operationsStaffUsers.get(0).getUsername()).isEqualTo(operationsStaffUser.getUsername());
        
        assertThat(systemAdminUsers).isNotEmpty();
        assertThat(systemAdminUsers).hasSize(1);
        assertThat(systemAdminUsers.get(0).getUsername()).isEqualTo(systemAdminUser.getUsername());
    }
    
    @Test
    @DisplayName("Test finding users by non-existent role name")
    public void testFindByNonExistentRoleName() {
        // When
        List<User> users = userRepository.findByRoleName("NON_EXISTENT_ROLE");
        
        // Then
        assertThat(users).isEmpty();
    }
    
    @Test
    @DisplayName("Test checking username existence")
    public void testExistsByUsername() {
        // When
        boolean existingUsername = userRepository.existsByUsername(regularUser.getUsername());
        boolean nonExistingUsername = userRepository.existsByUsername("non_existent_user");
        
        // Then
        assertThat(existingUsername).isTrue();
        assertThat(nonExistingUsername).isFalse();
    }
    
    @Test
    @DisplayName("Test checking email existence")
    public void testExistsByEmail() {
        // When
        boolean existingEmail = userRepository.existsByEmail(regularUser.getEmail());
        boolean nonExistingEmail = userRepository.existsByEmail("non_existent@dollarfunding.com");
        
        // Then
        assertThat(existingEmail).isTrue();
        assertThat(nonExistingEmail).isFalse();
    }
    
    @Test
    @DisplayName("Test finding users by username containing string")
    public void testFindByUsernameContainingIgnoreCase() {
        // When
        List<User> usersWithOps = userRepository.findByUsernameContainingIgnoreCase("ops");
        List<User> usersWithUser = userRepository.findByUsernameContainingIgnoreCase("user");
        
        // Then
        assertThat(usersWithOps).hasSize(1);
        assertThat(usersWithOps.get(0).getUsername()).isEqualTo(operationsStaffUser.getUsername());
        
        assertThat(usersWithUser).hasSize(3); // All users have 'user' in their username
    }
    
    @Test
    @DisplayName("Test finding users by email containing string")
    public void testFindByEmailContainingIgnoreCase() {
        // When
        List<User> usersWithAdmin = userRepository.findByEmailContainingIgnoreCase("admin");
        List<User> usersWithDollarfunding = userRepository.findByEmailContainingIgnoreCase("dollarfunding");
        
        // Then
        assertThat(usersWithAdmin).hasSize(1);
        assertThat(usersWithAdmin.get(0).getUsername()).isEqualTo(systemAdminUser.getUsername());
        
        assertThat(usersWithDollarfunding).hasSize(3); // All users have 'dollarfunding.com' in their email
    }
    
    @Test
    @DisplayName("Test finding enabled users")
    public void testFindByEnabledTrue() {
        // Create a disabled user
        User disabledUser = User.builder()
                .username("disabled_user")
                .password("password123")
                .email("disabled@dollarfunding.com")
                .enabled(false)
                .build();
        
        entityManager.persist(disabledUser);
        entityManager.flush();
        
        // When
        List<User> enabledUsers = userRepository.findByEnabledTrue();
        List<User> disabledUsers = userRepository.findByEnabledFalse();
        
        // Then
        assertThat(enabledUsers).hasSize(3); // Three enabled users
        assertThat(disabledUsers).hasSize(1); // One disabled user
        assertThat(disabledUsers.get(0).getUsername()).isEqualTo(disabledUser.getUsername());
    }
    
    @Test
    @DisplayName("Test finding locked users")
    public void testFindByAccountNonLockedFalse() {
        // Create a locked user
        User lockedUser = User.builder()
                .username("locked_user")
                .password("password123")
                .email("locked@dollarfunding.com")
                .accountNonLocked(false)
                .build();
        
        entityManager.persist(lockedUser);
        entityManager.flush();
        
        // When
        List<User> lockedUsers = userRepository.findByAccountNonLockedFalse();
        
        // Then
        assertThat(lockedUsers).hasSize(1);
        assertThat(lockedUsers.get(0).getUsername()).isEqualTo(lockedUser.getUsername());
    }
}