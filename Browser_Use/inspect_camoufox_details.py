from camoufox import AsyncCamoufox, AsyncNewBrowser
import inspect

print("=== AsyncCamoufox doc ===")
print(AsyncCamoufox.__doc__)
print("\n=== AsyncCamoufox init signature ===")
print(inspect.signature(AsyncCamoufox.__init__))

print("\n=== AsyncNewBrowser doc ===")
print(AsyncNewBrowser.__doc__)
print("\n=== AsyncNewBrowser init signature ===")
print(inspect.signature(AsyncNewBrowser.__init__))
