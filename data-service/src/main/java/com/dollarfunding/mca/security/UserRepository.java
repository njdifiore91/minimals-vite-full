package com.dollarfunding.mca.security;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * Spring Data JPA repository interface for User entities that provides database access methods
 * for user information. It extends JpaRepository to inherit standard CRUD operations and adds
 * custom query methods for finding users by username, email, and role.
 * 
 * This repository is essential for user authentication and management within the MCA Application
 * Processing System. It supports the JWT authentication system integration with the Minimal UI Kit
 * frontend and enables role-based access control for Operations Staff and System Admin roles.
 */
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    /**
     * Find a user by username.
     * 
     * @param username the username to search for
     * @return an Optional containing the user if found, or empty if not found
     */
    Optional<User> findByUsername(String username);
    
    /**
     * Find a user by email address.
     * 
     * @param email the email address to search for
     * @return an Optional containing the user if found, or empty if not found
     */
    Optional<User> findByEmail(String email);
    
    /**
     * Find a user by username or email address.
     * This is useful for login functionality where users can authenticate with either username or email.
     * 
     * @param username the username to search for
     * @param email the email address to search for
     * @return an Optional containing the user if found, or empty if not found
     */
    Optional<User> findByUsernameOrEmail(String username, String email);
    
    /**
     * Check if a username already exists.
     * 
     * @param username the username to check
     * @return true if the username exists, false otherwise
     */
    boolean existsByUsername(String username);
    
    /**
     * Check if an email address already exists.
     * 
     * @param email the email address to check
     * @return true if the email exists, false otherwise
     */
    boolean existsByEmail(String email);
    
    /**
     * Find all users with a specific role.
     * 
     * @param roleName the role name to search for
     * @return a list of users with the specified role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = :roleName")
    List<User> findByRoleName(@Param("roleName") String roleName);
    
    /**
     * Find all Operations Staff users.
     * 
     * @return a list of users with the Operations Staff role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = '" + Role.ROLE_OPERATIONS_STAFF + "'")
    List<User> findAllOperationsStaff();
    
    /**
     * Find all System Admin users.
     * 
     * @return a list of users with the System Admin role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = '" + Role.ROLE_SYSTEM_ADMIN + "'")
    List<User> findAllSystemAdmins();
    
    /**
     * Find all enabled users.
     * 
     * @return a list of enabled users
     */
    List<User> findByEnabledTrue();
    
    /**
     * Find all disabled users.
     * 
     * @return a list of disabled users
     */
    List<User> findByEnabledFalse();
    
    /**
     * Find all locked users.
     * 
     * @return a list of locked users
     */
    List<User> findByAccountNonLockedFalse();
    
    /**
     * Find all users with expired credentials.
     * 
     * @return a list of users with expired credentials
     */
    List<User> findByCredentialsNonExpiredFalse();
    
    /**
     * Find all users with expired accounts.
     * 
     * @return a list of users with expired accounts
     */
    List<User> findByAccountNonExpiredFalse();
    
    /**
     * Find all users with a specific role that are enabled.
     * 
     * @param roleName the role name to search for
     * @return a list of enabled users with the specified role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = :roleName AND u.enabled = true")
    List<User> findByRoleNameAndEnabled(@Param("roleName") String roleName);
    
    /**
     * Find users by first name containing the given string (case insensitive).
     * 
     * @param firstName the first name pattern to search for
     * @return a list of users matching the first name pattern
     */
    List<User> findByFirstNameContainingIgnoreCase(String firstName);
    
    /**
     * Find users by last name containing the given string (case insensitive).
     * 
     * @param lastName the last name pattern to search for
     * @return a list of users matching the last name pattern
     */
    List<User> findByLastNameContainingIgnoreCase(String lastName);
    
    /**
     * Find users by first name and last name containing the given strings (case insensitive).
     * 
     * @param firstName the first name pattern to search for
     * @param lastName the last name pattern to search for
     * @return a list of users matching both the first name and last name patterns
     */
    List<User> findByFirstNameContainingIgnoreCaseAndLastNameContainingIgnoreCase(String firstName, String lastName);
    
    /**
     * Count the number of users with a specific role.
     * 
     * @param roleName the role name to count
     * @return the number of users with the specified role
     */
    @Query("SELECT COUNT(u) FROM User u JOIN u.roles r WHERE r.name = :roleName")
    long countByRoleName(@Param("roleName") String roleName);
    
    /**
     * Count the number of Operations Staff users.
     * 
     * @return the number of users with the Operations Staff role
     */
    @Query("SELECT COUNT(u) FROM User u JOIN u.roles r WHERE r.name = '" + Role.ROLE_OPERATIONS_STAFF + "'")
    long countOperationsStaff();
    
    /**
     * Count the number of System Admin users.
     * 
     * @return the number of users with the System Admin role
     */
    @Query("SELECT COUNT(u) FROM User u JOIN u.roles r WHERE r.name = '" + Role.ROLE_SYSTEM_ADMIN + "'")
    long countSystemAdmins();
}