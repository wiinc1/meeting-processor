from selenium import webdriver
import time

# Initialize the Safari driver
driver = webdriver.Safari()

# Navigate to a website
driver.get('https://otter.ai/signin')

# Wait for a few seconds to see if it loads
time.sleep(10)

# Print the page title to verify it's working
print(f"Page title: {driver.title}")

# Close the browser
driver.quit()

print("Test completed successfully!") 