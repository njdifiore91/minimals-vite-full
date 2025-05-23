package com.dollarfunding.mca.security;

import com.dollarfunding.mca.entity.User;
import com.dollarfunding.mca.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Test class for UserRepository that verifies the correct implementation of database access methods
 * for user information. Tests finding users by username, email, and role, as well as checking
 * username and email existence.
 */
@DataJpaTest
public class UserRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private UserRepository userRepository;

    private User operationsUser;
    private User adminUser;
    private User secondOperationsUser;

    @BeforeEach
    public void setup() {
        // Create test users with different roles
        operationsUser = new User();
        operationsUser.setUsername("operations_user");
        operationsUser.setEmail("operations@dollarfunding.com");
        operationsUser.setPassword("$2a$10$encrypted_password_hash"); // Simulated bcrypt hash
        operationsUser.setRole("OPERATIONS_STAFF");
        operationsUser.setEnabled(true);
        
        adminUser = new User();
        adminUser.setUsername("admin_user");
        adminUser.setEmail("admin@dollarfunding.com");
        adminUser.setPassword("$2a$10$encrypted_password_hash"); // Simulated bcrypt hash
        adminUser.setRole("SYSTEM_ADMIN");
        adminUser.setEnabled(true);
        
        secondOperationsUser = new User();
        secondOperationsUser.setUsername("operations_user2");
        secondOperationsUser.setEmail("operations2@dollarfunding.com");
        secondOperationsUser.setPassword("$2a$10$encrypted_password_hash"); // Simulated bcrypt hash
        secondOperationsUser.setRole("OPERATIONS_STAFF");
        secondOperationsUser.setEnabled(true);
        
        // Persist test users to the in-memory database
        entityManager.persist(operationsUser);
        entityManager.persist(adminUser);
        entityManager.persist(secondOperationsUser);
        entityManager.flush();
    }

    /**
     * Test finding a user by username.
     * Verifies that the repository correctly retrieves a user when given a valid username.
     */
    @Test
    public void testFindByUsername() {
        // When
        Optional<User> foundUser = userRepository.findByUsername(operationsUser.getUsername());
        
        // Then
        assertThat(foundUser).isPresent();
        assertThat(foundUser.get().getEmail()).isEqualTo(operationsUser.getEmail());
        assertThat(foundUser.get().getRole()).isEqualTo("OPERATIONS_STAFF");
    }
    
    /**
     * Test finding a user by username when the username doesn't exist.
     * Verifies that the repository returns an empty Optional when no user is found.
     */
    @Test
    public void testFindByUsername_NotFound() {
        // When
        Optional<User> foundUser = userRepository.findByUsername("nonexistent_user");
        
        // Then
        assertThat(foundUser).isEmpty();
    }

    /**
     * Test finding a user by email.
     * Verifies that the repository correctly retrieves a user when given a valid email address.
     */
    @Test
    public void testFindByEmail() {
        // When
        Optional<User> foundUser = userRepository.findByEmail(adminUser.getEmail());
        
        // Then
        assertThat(foundUser).isPresent();
        assertThat(foundUser.get().getUsername()).isEqualTo(adminUser.getUsername());
        assertThat(foundUser.get().getRole()).isEqualTo("SYSTEM_ADMIN");
    }
    
    /**
     * Test finding a user by email when the email doesn't exist.
     * Verifies that the repository returns an empty Optional when no user is found.
     */
    @Test
    public void testFindByEmail_NotFound() {
        // When
        Optional<User> foundUser = userRepository.findByEmail("nonexistent@dollarfunding.com");
        
        // Then
        assertThat(foundUser).isEmpty();
    }

    /**
     * Test finding users by role.
     * Verifies that the repository correctly retrieves all users with a specific role.
     */
    @Test
    public void testFindByRole() {
        // When
        List<User> operationsUsers = userRepository.findByRole("OPERATIONS_STAFF");
        List<User> adminUsers = userRepository.findByRole("SYSTEM_ADMIN");
        
        // Then
        assertThat(operationsUsers).hasSize(2);
        assertThat(adminUsers).hasSize(1);
        
        assertThat(operationsUsers)
            .extracting(User::getUsername)
            .containsExactlyInAnyOrder(operationsUser.getUsername(), secondOperationsUser.getUsername());
        
        assertThat(adminUsers)
            .extracting(User::getUsername)
            .containsExactly(adminUser.getUsername());
    }
    
    /**
     * Test finding users by a role that doesn't exist in the system.
     * Verifies that the repository returns an empty list when no users have the specified role.
     */
    @Test
    public void testFindByRole_NotFound() {
        // When
        List<User> users = userRepository.findByRole("NONEXISTENT_ROLE");
        
        // Then
        assertThat(users).isEmpty();
    }

    /**
     * Test checking if a username exists.
     * Verifies that the repository correctly identifies existing usernames.
     */
    @Test
    public void testExistsByUsername() {
        // When
        boolean exists = userRepository.existsByUsername(operationsUser.getUsername());
        boolean notExists = userRepository.existsByUsername("nonexistent_user");
        
        // Then
        assertThat(exists).isTrue();
        assertThat(notExists).isFalse();
    }

    /**
     * Test checking if an email exists.
     * Verifies that the repository correctly identifies existing email addresses.
     */
    @Test
    public void testExistsByEmail() {
        // When
        boolean exists = userRepository.existsByEmail(adminUser.getEmail());
        boolean notExists = userRepository.existsByEmail("nonexistent@dollarfunding.com");
        
        // Then
        assertThat(exists).isTrue();
        assertThat(notExists).isFalse();
    }
}