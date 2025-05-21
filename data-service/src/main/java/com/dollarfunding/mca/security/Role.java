package com.dollarfunding.mca.security;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import com.dollarfunding.mca.security.User;

/**
 * Entity class representing user roles in the database.
 * This entity is essential for role-based access control as it defines
 * the available roles in the system.
 */
@Entity
@Table(name = "roles")
public class Role {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "Role name is required")
    @Size(max = 50, message = "Role name cannot exceed 50 characters")
    @Column(name = "name", unique = true, nullable = false, length = 50)
    private String name;

    @Size(max = 255, message = "Description cannot exceed 255 characters")
    @Column(name = "description", length = 255)
    private String description;

    @ManyToMany(mappedBy = "roles")
    private Set<User> users = new HashSet<>();

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * Default constructor required by JPA.
     */
    public Role() {
    }

    /**
     * Constructor with role name.
     *
     * @param name the role name
     */
    public Role(String name) {
        this.name = name;
    }

    /**
     * Constructor with role name and description.
     *
     * @param name        the role name
     * @param description the role description
     */
    public Role(String name, String description) {
        this.name = name;
        this.description = description;
    }

    /**
     * Pre-persist lifecycle callback to set default values before persisting.
     */
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    /**
     * Pre-update lifecycle callback to update the updatedAt timestamp.
     */
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    /**
     * Constants for role names used in the application.
     */
    public static final String ROLE_OPERATIONS_STAFF = "ROLE_OPERATIONS_STAFF";
    public static final String ROLE_SYSTEM_ADMIN = "ROLE_SYSTEM_ADMIN";
    
    /**
     * Checks if this role is for Operations Staff.
     *
     * @return true if this role is for Operations Staff, false otherwise
     */
    public boolean isOperationsStaff() {
        return ROLE_OPERATIONS_STAFF.equals(name);
    }

    /**
     * Checks if this role is for System Admin.
     *
     * @return true if this role is for System Admin, false otherwise
     */
    public boolean isSystemAdmin() {
        return ROLE_SYSTEM_ADMIN.equals(name);
    }

    // Getters and Setters

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Set<User> getUsers() {
        return users;
    }

    public void setUsers(Set<User> users) {
        this.users = users;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((name == null) ? 0 : name.hashCode());
        return result;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) return true;
        if (obj == null) return false;
        if (getClass() != obj.getClass()) return false;
        Role other = (Role) obj;
        if (name == null) {
            return other.name == null;
        } else {
            return name.equals(other.name);
        }
    }

    @Override
    public String toString() {
        return "Role [id=" + id + ", name=" + name + ", description=" + description + "]";
    }

    /**
     * Builder class for Role entity to facilitate creation of Role objects.
     */
    public static class Builder {
        private String name;
        private String description;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder description(String description) {
            this.description = description;
            return this;
        }

        public Role build() {
            return new Role(name, description);
        }
    }

    /**
     * Creates a new Builder instance.
     *
     * @return a new Builder instance
     */
    public static Builder builder() {
        return new Builder();
    }
    
    /**
     * Creates a new Operations Staff role.
     *
     * @return a new Role instance for Operations Staff
     */
    public static Role createOperationsStaffRole() {
        return new Role(ROLE_OPERATIONS_STAFF, "Operations Staff with access to read all data and write application data");
    }
    
    /**
     * Creates a new System Admin role.
     *
     * @return a new Role instance for System Admin
     */
    public static Role createSystemAdminRole() {
        return new Role(ROLE_SYSTEM_ADMIN, "System Admin with full access to all endpoints and webhook configuration");
    }
}